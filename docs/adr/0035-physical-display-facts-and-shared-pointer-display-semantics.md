# ADR 0035 — Physical Display Facts, Suitability Policy, and Shared Pointer/Display Settings Semantics

Status: **Accepted and implemented**

Date: 2026-09-03

Extends: ADR 0020 (runtime-neutral input, controller support, physical-input authority), ADR 0026 (resolution-adaptive layout). Replaces neither; both remain authoritative for their scope.

## Context

ADR 0026 made the live usable viewport the layout authority and forbade model-specific UI forks. ADR 0020 made physical input platform-owned and interaction profiles runtime-neutral. The 2026-09-03 display/input tranche (T01–T09) implemented the missing seams between those contracts: where physical display facts come from, how suitability is decided without whitelists, how physical touch-target floors are shared, who owns pointer settings, and how installer and Parent consume both without touching backend commands.

The T10 forbidden-outcome sweep and the 17-question adversarial review are preserved by reference in the T10 attempt report (reference evidence: `phases/bootstrap/tasks/T10-R/carry-forward/predecessor.patch` in the T-BAG run); they are not silently re-authored here.

## Decision

### 1. Display-metrics authority (`src/greia_platform/display_metrics.py`)

`DisplayMetrics` carries raw physical facts only (pixel dimensions, physical millimetres, source). Derived values (orientation, aspect ratio, densities, diagonal) are computed properties, never persisted. `sanitize_display_metrics` applies named broad bounds: bad pixels yield `None`; missing, partial, out-of-range, or absurd-DPI physical facts yield explicitly unknown physical size — never an invented geometry and never an assumed 96 DPI.

### 2. Suitability is envelope comparison, not a whitelist (`DisplayPolicy`)

`DisplayPolicy` with its `phase0()` factory compares each candidate mode against pixel and physical envelopes. `1024×600` appears only as preferred defaults, never as an equality branch. Verdicts are `SUPPORTED`, `SUPPORTED_WITH_REFLOW`, `UNKNOWN_PHYSICAL_SIZE`, or unsupported variants. Unknown physical size fails open in UI flows and never blocks installation; provably-unsupported geometry blocks destructive installation with a clear message.

### 3. Physical minimums are shared, bounded, and never global scaling (`PhysicalUiPolicy`, trusted floor)

`PhysicalUiPolicy.minimum_pixels` converts a millimetre floor through trustworthy density, else a clamped fallback, always within 8–320 px. It sizes shared interactive minimums; it never scales a layout globally. The trusted-action floor (`TRUSTED_ACTION_MINIMUM_MM = 10.0`, `resolve_trusted_action_minimum_px`) is defined once in `src/greia_launcher/system_chrome.py` and imported by navigation and profile chrome; no second floor helper exists. `responsive_layout.py` stays geometry-only: no subprocess, no `xrandr`/`xinput`, no model branches.

### 4. Pointer authority: store → watcher → Legacy-X backend

`HardwareSettingsStore` (schema v2, tap-OFF canonical) is the single desired-state owner. The session watcher applies it through the Legacy-X hardware-session controller; the installed X session wrapper holds no pointer commands. Pointer classification is properties-primary with name-substring fallback; exposed labels are generic kind labels (`Touchpad`, `Mouse`, `Pointer`, `Touchscreen`) with occurrence counts — never backend ids or device names. Pointer preview (installer) and pointer controls (Parent panel) go only through the narrow `PointerSettingsController.apply_pointer_settings` seam with semantic settings; unknown capability fails open to full controls rather than trapping the user. Tap-to-click default OFF is owned by `AGENTS.md` platform policy and reconciled across TOML, store defaults, installer copy, and Parent copy by this tranche.

### 5. Shared installer/Parent semantics

Installer pointer setup and the Parent pointer tab share `SPEED_PRESETS`/`preset_to_speed`/`speed_to_preset`/`speed_preset_names` (single location, no forked table), capability gating, central-defaults reset, and `filter_supported_modes` + `DisplayPolicy.phase0()` over cached probe metrics. Parent `GET`/`PUT`/`reset /api/v1/settings/hardware` is typed and strict (field allowlist, real-bool/numerics checks, bounds in the store); raw backend vocabulary (device ids, property names, matrices, commands) is rejected, and the GET backend id is read-only display metadata, never executed.

### 6. Backend isolation

`xinput`/`xrandr` command vocabulary lives only in the Legacy-X translation seam (`hal_legacy_x.py`), the pre-existing brightness fallback (`system_controls_legacy_x.py`), and the `activity_backend_policy.py` forbidden-import list. Installer, Parent UI, launcher chrome, and layout code never invoke backend commands. No CTM command is issued in any ordinary apply path; no hard-coded device names exist in generic startup.

## Consequences

- UI/policy code must not branch on hardware model names or resolution equality; envelope comparison and viewport geometry are the mechanisms.
- New pointer/display settings surface through the store and the existing seams; no parallel stores, daemons, or polling loops.
- Physical hardware lanes (Acer panel, USB mouse, second display, resolution change) remain human-executed acceptance on the frozen candidate; source tests do not certify them.
- `docs/product/ACTIVITY_INPUT_STANDARDS.md` is intentionally untouched: pointer interaction semantics did not change (settings UX only).
